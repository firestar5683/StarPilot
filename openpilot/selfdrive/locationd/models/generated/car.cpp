#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_4576239672767356577) {
   out_4576239672767356577[0] = delta_x[0] + nom_x[0];
   out_4576239672767356577[1] = delta_x[1] + nom_x[1];
   out_4576239672767356577[2] = delta_x[2] + nom_x[2];
   out_4576239672767356577[3] = delta_x[3] + nom_x[3];
   out_4576239672767356577[4] = delta_x[4] + nom_x[4];
   out_4576239672767356577[5] = delta_x[5] + nom_x[5];
   out_4576239672767356577[6] = delta_x[6] + nom_x[6];
   out_4576239672767356577[7] = delta_x[7] + nom_x[7];
   out_4576239672767356577[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7162114440537636591) {
   out_7162114440537636591[0] = -nom_x[0] + true_x[0];
   out_7162114440537636591[1] = -nom_x[1] + true_x[1];
   out_7162114440537636591[2] = -nom_x[2] + true_x[2];
   out_7162114440537636591[3] = -nom_x[3] + true_x[3];
   out_7162114440537636591[4] = -nom_x[4] + true_x[4];
   out_7162114440537636591[5] = -nom_x[5] + true_x[5];
   out_7162114440537636591[6] = -nom_x[6] + true_x[6];
   out_7162114440537636591[7] = -nom_x[7] + true_x[7];
   out_7162114440537636591[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6671036100293030853) {
   out_6671036100293030853[0] = 1.0;
   out_6671036100293030853[1] = 0.0;
   out_6671036100293030853[2] = 0.0;
   out_6671036100293030853[3] = 0.0;
   out_6671036100293030853[4] = 0.0;
   out_6671036100293030853[5] = 0.0;
   out_6671036100293030853[6] = 0.0;
   out_6671036100293030853[7] = 0.0;
   out_6671036100293030853[8] = 0.0;
   out_6671036100293030853[9] = 0.0;
   out_6671036100293030853[10] = 1.0;
   out_6671036100293030853[11] = 0.0;
   out_6671036100293030853[12] = 0.0;
   out_6671036100293030853[13] = 0.0;
   out_6671036100293030853[14] = 0.0;
   out_6671036100293030853[15] = 0.0;
   out_6671036100293030853[16] = 0.0;
   out_6671036100293030853[17] = 0.0;
   out_6671036100293030853[18] = 0.0;
   out_6671036100293030853[19] = 0.0;
   out_6671036100293030853[20] = 1.0;
   out_6671036100293030853[21] = 0.0;
   out_6671036100293030853[22] = 0.0;
   out_6671036100293030853[23] = 0.0;
   out_6671036100293030853[24] = 0.0;
   out_6671036100293030853[25] = 0.0;
   out_6671036100293030853[26] = 0.0;
   out_6671036100293030853[27] = 0.0;
   out_6671036100293030853[28] = 0.0;
   out_6671036100293030853[29] = 0.0;
   out_6671036100293030853[30] = 1.0;
   out_6671036100293030853[31] = 0.0;
   out_6671036100293030853[32] = 0.0;
   out_6671036100293030853[33] = 0.0;
   out_6671036100293030853[34] = 0.0;
   out_6671036100293030853[35] = 0.0;
   out_6671036100293030853[36] = 0.0;
   out_6671036100293030853[37] = 0.0;
   out_6671036100293030853[38] = 0.0;
   out_6671036100293030853[39] = 0.0;
   out_6671036100293030853[40] = 1.0;
   out_6671036100293030853[41] = 0.0;
   out_6671036100293030853[42] = 0.0;
   out_6671036100293030853[43] = 0.0;
   out_6671036100293030853[44] = 0.0;
   out_6671036100293030853[45] = 0.0;
   out_6671036100293030853[46] = 0.0;
   out_6671036100293030853[47] = 0.0;
   out_6671036100293030853[48] = 0.0;
   out_6671036100293030853[49] = 0.0;
   out_6671036100293030853[50] = 1.0;
   out_6671036100293030853[51] = 0.0;
   out_6671036100293030853[52] = 0.0;
   out_6671036100293030853[53] = 0.0;
   out_6671036100293030853[54] = 0.0;
   out_6671036100293030853[55] = 0.0;
   out_6671036100293030853[56] = 0.0;
   out_6671036100293030853[57] = 0.0;
   out_6671036100293030853[58] = 0.0;
   out_6671036100293030853[59] = 0.0;
   out_6671036100293030853[60] = 1.0;
   out_6671036100293030853[61] = 0.0;
   out_6671036100293030853[62] = 0.0;
   out_6671036100293030853[63] = 0.0;
   out_6671036100293030853[64] = 0.0;
   out_6671036100293030853[65] = 0.0;
   out_6671036100293030853[66] = 0.0;
   out_6671036100293030853[67] = 0.0;
   out_6671036100293030853[68] = 0.0;
   out_6671036100293030853[69] = 0.0;
   out_6671036100293030853[70] = 1.0;
   out_6671036100293030853[71] = 0.0;
   out_6671036100293030853[72] = 0.0;
   out_6671036100293030853[73] = 0.0;
   out_6671036100293030853[74] = 0.0;
   out_6671036100293030853[75] = 0.0;
   out_6671036100293030853[76] = 0.0;
   out_6671036100293030853[77] = 0.0;
   out_6671036100293030853[78] = 0.0;
   out_6671036100293030853[79] = 0.0;
   out_6671036100293030853[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_937155241058689280) {
   out_937155241058689280[0] = state[0];
   out_937155241058689280[1] = state[1];
   out_937155241058689280[2] = state[2];
   out_937155241058689280[3] = state[3];
   out_937155241058689280[4] = state[4];
   out_937155241058689280[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_937155241058689280[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_937155241058689280[7] = state[7];
   out_937155241058689280[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6680942651904151339) {
   out_6680942651904151339[0] = 1;
   out_6680942651904151339[1] = 0;
   out_6680942651904151339[2] = 0;
   out_6680942651904151339[3] = 0;
   out_6680942651904151339[4] = 0;
   out_6680942651904151339[5] = 0;
   out_6680942651904151339[6] = 0;
   out_6680942651904151339[7] = 0;
   out_6680942651904151339[8] = 0;
   out_6680942651904151339[9] = 0;
   out_6680942651904151339[10] = 1;
   out_6680942651904151339[11] = 0;
   out_6680942651904151339[12] = 0;
   out_6680942651904151339[13] = 0;
   out_6680942651904151339[14] = 0;
   out_6680942651904151339[15] = 0;
   out_6680942651904151339[16] = 0;
   out_6680942651904151339[17] = 0;
   out_6680942651904151339[18] = 0;
   out_6680942651904151339[19] = 0;
   out_6680942651904151339[20] = 1;
   out_6680942651904151339[21] = 0;
   out_6680942651904151339[22] = 0;
   out_6680942651904151339[23] = 0;
   out_6680942651904151339[24] = 0;
   out_6680942651904151339[25] = 0;
   out_6680942651904151339[26] = 0;
   out_6680942651904151339[27] = 0;
   out_6680942651904151339[28] = 0;
   out_6680942651904151339[29] = 0;
   out_6680942651904151339[30] = 1;
   out_6680942651904151339[31] = 0;
   out_6680942651904151339[32] = 0;
   out_6680942651904151339[33] = 0;
   out_6680942651904151339[34] = 0;
   out_6680942651904151339[35] = 0;
   out_6680942651904151339[36] = 0;
   out_6680942651904151339[37] = 0;
   out_6680942651904151339[38] = 0;
   out_6680942651904151339[39] = 0;
   out_6680942651904151339[40] = 1;
   out_6680942651904151339[41] = 0;
   out_6680942651904151339[42] = 0;
   out_6680942651904151339[43] = 0;
   out_6680942651904151339[44] = 0;
   out_6680942651904151339[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6680942651904151339[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6680942651904151339[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6680942651904151339[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6680942651904151339[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6680942651904151339[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6680942651904151339[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6680942651904151339[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6680942651904151339[53] = -9.8100000000000005*dt;
   out_6680942651904151339[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6680942651904151339[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6680942651904151339[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6680942651904151339[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6680942651904151339[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6680942651904151339[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6680942651904151339[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6680942651904151339[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6680942651904151339[62] = 0;
   out_6680942651904151339[63] = 0;
   out_6680942651904151339[64] = 0;
   out_6680942651904151339[65] = 0;
   out_6680942651904151339[66] = 0;
   out_6680942651904151339[67] = 0;
   out_6680942651904151339[68] = 0;
   out_6680942651904151339[69] = 0;
   out_6680942651904151339[70] = 1;
   out_6680942651904151339[71] = 0;
   out_6680942651904151339[72] = 0;
   out_6680942651904151339[73] = 0;
   out_6680942651904151339[74] = 0;
   out_6680942651904151339[75] = 0;
   out_6680942651904151339[76] = 0;
   out_6680942651904151339[77] = 0;
   out_6680942651904151339[78] = 0;
   out_6680942651904151339[79] = 0;
   out_6680942651904151339[80] = 1;
}
void h_25(double *state, double *unused, double *out_1771039490862882834) {
   out_1771039490862882834[0] = state[6];
}
void H_25(double *state, double *unused, double *out_1250301932680828952) {
   out_1250301932680828952[0] = 0;
   out_1250301932680828952[1] = 0;
   out_1250301932680828952[2] = 0;
   out_1250301932680828952[3] = 0;
   out_1250301932680828952[4] = 0;
   out_1250301932680828952[5] = 0;
   out_1250301932680828952[6] = 1;
   out_1250301932680828952[7] = 0;
   out_1250301932680828952[8] = 0;
}
void h_24(double *state, double *unused, double *out_312253478356362907) {
   out_312253478356362907[0] = state[4];
   out_312253478356362907[1] = state[5];
}
void H_24(double *state, double *unused, double *out_922347666324670614) {
   out_922347666324670614[0] = 0;
   out_922347666324670614[1] = 0;
   out_922347666324670614[2] = 0;
   out_922347666324670614[3] = 0;
   out_922347666324670614[4] = 1;
   out_922347666324670614[5] = 0;
   out_922347666324670614[6] = 0;
   out_922347666324670614[7] = 0;
   out_922347666324670614[8] = 0;
   out_922347666324670614[9] = 0;
   out_922347666324670614[10] = 0;
   out_922347666324670614[11] = 0;
   out_922347666324670614[12] = 0;
   out_922347666324670614[13] = 0;
   out_922347666324670614[14] = 1;
   out_922347666324670614[15] = 0;
   out_922347666324670614[16] = 0;
   out_922347666324670614[17] = 0;
}
void h_30(double *state, double *unused, double *out_7811593157953647596) {
   out_7811593157953647596[0] = state[4];
}
void H_30(double *state, double *unused, double *out_3768634891188077579) {
   out_3768634891188077579[0] = 0;
   out_3768634891188077579[1] = 0;
   out_3768634891188077579[2] = 0;
   out_3768634891188077579[3] = 0;
   out_3768634891188077579[4] = 1;
   out_3768634891188077579[5] = 0;
   out_3768634891188077579[6] = 0;
   out_3768634891188077579[7] = 0;
   out_3768634891188077579[8] = 0;
}
void h_26(double *state, double *unused, double *out_2809919890292801951) {
   out_2809919890292801951[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2491201386193227272) {
   out_2491201386193227272[0] = 0;
   out_2491201386193227272[1] = 0;
   out_2491201386193227272[2] = 0;
   out_2491201386193227272[3] = 0;
   out_2491201386193227272[4] = 0;
   out_2491201386193227272[5] = 0;
   out_2491201386193227272[6] = 0;
   out_2491201386193227272[7] = 1;
   out_2491201386193227272[8] = 0;
}
void h_27(double *state, double *unused, double *out_6592889242767479272) {
   out_6592889242767479272[0] = state[3];
}
void H_27(double *state, double *unused, double *out_5452157709247204157) {
   out_5452157709247204157[0] = 0;
   out_5452157709247204157[1] = 0;
   out_5452157709247204157[2] = 0;
   out_5452157709247204157[3] = 1;
   out_5452157709247204157[4] = 0;
   out_5452157709247204157[5] = 0;
   out_5452157709247204157[6] = 0;
   out_5452157709247204157[7] = 0;
   out_5452157709247204157[8] = 0;
}
void h_29(double *state, double *unused, double *out_6868083305051985161) {
   out_6868083305051985161[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2767163053132387062) {
   out_2767163053132387062[0] = 0;
   out_2767163053132387062[1] = 1;
   out_2767163053132387062[2] = 0;
   out_2767163053132387062[3] = 0;
   out_2767163053132387062[4] = 0;
   out_2767163053132387062[5] = 0;
   out_2767163053132387062[6] = 0;
   out_2767163053132387062[7] = 0;
   out_2767163053132387062[8] = 0;
}
void h_28(double *state, double *unused, double *out_3988483921958781621) {
   out_3988483921958781621[0] = state[0];
}
void H_28(double *state, double *unused, double *out_803532781567060811) {
   out_803532781567060811[0] = 1;
   out_803532781567060811[1] = 0;
   out_803532781567060811[2] = 0;
   out_803532781567060811[3] = 0;
   out_803532781567060811[4] = 0;
   out_803532781567060811[5] = 0;
   out_803532781567060811[6] = 0;
   out_803532781567060811[7] = 0;
   out_803532781567060811[8] = 0;
}
void h_31(double *state, double *unused, double *out_2046233553147388723) {
   out_2046233553147388723[0] = state[8];
}
void H_31(double *state, double *unused, double *out_3117409488426578748) {
   out_3117409488426578748[0] = 0;
   out_3117409488426578748[1] = 0;
   out_3117409488426578748[2] = 0;
   out_3117409488426578748[3] = 0;
   out_3117409488426578748[4] = 0;
   out_3117409488426578748[5] = 0;
   out_3117409488426578748[6] = 0;
   out_3117409488426578748[7] = 0;
   out_3117409488426578748[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_4576239672767356577) {
  err_fun(nom_x, delta_x, out_4576239672767356577);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7162114440537636591) {
  inv_err_fun(nom_x, true_x, out_7162114440537636591);
}
void car_H_mod_fun(double *state, double *out_6671036100293030853) {
  H_mod_fun(state, out_6671036100293030853);
}
void car_f_fun(double *state, double dt, double *out_937155241058689280) {
  f_fun(state,  dt, out_937155241058689280);
}
void car_F_fun(double *state, double dt, double *out_6680942651904151339) {
  F_fun(state,  dt, out_6680942651904151339);
}
void car_h_25(double *state, double *unused, double *out_1771039490862882834) {
  h_25(state, unused, out_1771039490862882834);
}
void car_H_25(double *state, double *unused, double *out_1250301932680828952) {
  H_25(state, unused, out_1250301932680828952);
}
void car_h_24(double *state, double *unused, double *out_312253478356362907) {
  h_24(state, unused, out_312253478356362907);
}
void car_H_24(double *state, double *unused, double *out_922347666324670614) {
  H_24(state, unused, out_922347666324670614);
}
void car_h_30(double *state, double *unused, double *out_7811593157953647596) {
  h_30(state, unused, out_7811593157953647596);
}
void car_H_30(double *state, double *unused, double *out_3768634891188077579) {
  H_30(state, unused, out_3768634891188077579);
}
void car_h_26(double *state, double *unused, double *out_2809919890292801951) {
  h_26(state, unused, out_2809919890292801951);
}
void car_H_26(double *state, double *unused, double *out_2491201386193227272) {
  H_26(state, unused, out_2491201386193227272);
}
void car_h_27(double *state, double *unused, double *out_6592889242767479272) {
  h_27(state, unused, out_6592889242767479272);
}
void car_H_27(double *state, double *unused, double *out_5452157709247204157) {
  H_27(state, unused, out_5452157709247204157);
}
void car_h_29(double *state, double *unused, double *out_6868083305051985161) {
  h_29(state, unused, out_6868083305051985161);
}
void car_H_29(double *state, double *unused, double *out_2767163053132387062) {
  H_29(state, unused, out_2767163053132387062);
}
void car_h_28(double *state, double *unused, double *out_3988483921958781621) {
  h_28(state, unused, out_3988483921958781621);
}
void car_H_28(double *state, double *unused, double *out_803532781567060811) {
  H_28(state, unused, out_803532781567060811);
}
void car_h_31(double *state, double *unused, double *out_2046233553147388723) {
  h_31(state, unused, out_2046233553147388723);
}
void car_H_31(double *state, double *unused, double *out_3117409488426578748) {
  H_31(state, unused, out_3117409488426578748);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
