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
void err_fun(double *nom_x, double *delta_x, double *out_8308214496735031777) {
   out_8308214496735031777[0] = delta_x[0] + nom_x[0];
   out_8308214496735031777[1] = delta_x[1] + nom_x[1];
   out_8308214496735031777[2] = delta_x[2] + nom_x[2];
   out_8308214496735031777[3] = delta_x[3] + nom_x[3];
   out_8308214496735031777[4] = delta_x[4] + nom_x[4];
   out_8308214496735031777[5] = delta_x[5] + nom_x[5];
   out_8308214496735031777[6] = delta_x[6] + nom_x[6];
   out_8308214496735031777[7] = delta_x[7] + nom_x[7];
   out_8308214496735031777[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8999766425853420329) {
   out_8999766425853420329[0] = -nom_x[0] + true_x[0];
   out_8999766425853420329[1] = -nom_x[1] + true_x[1];
   out_8999766425853420329[2] = -nom_x[2] + true_x[2];
   out_8999766425853420329[3] = -nom_x[3] + true_x[3];
   out_8999766425853420329[4] = -nom_x[4] + true_x[4];
   out_8999766425853420329[5] = -nom_x[5] + true_x[5];
   out_8999766425853420329[6] = -nom_x[6] + true_x[6];
   out_8999766425853420329[7] = -nom_x[7] + true_x[7];
   out_8999766425853420329[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8671923853756600219) {
   out_8671923853756600219[0] = 1.0;
   out_8671923853756600219[1] = 0.0;
   out_8671923853756600219[2] = 0.0;
   out_8671923853756600219[3] = 0.0;
   out_8671923853756600219[4] = 0.0;
   out_8671923853756600219[5] = 0.0;
   out_8671923853756600219[6] = 0.0;
   out_8671923853756600219[7] = 0.0;
   out_8671923853756600219[8] = 0.0;
   out_8671923853756600219[9] = 0.0;
   out_8671923853756600219[10] = 1.0;
   out_8671923853756600219[11] = 0.0;
   out_8671923853756600219[12] = 0.0;
   out_8671923853756600219[13] = 0.0;
   out_8671923853756600219[14] = 0.0;
   out_8671923853756600219[15] = 0.0;
   out_8671923853756600219[16] = 0.0;
   out_8671923853756600219[17] = 0.0;
   out_8671923853756600219[18] = 0.0;
   out_8671923853756600219[19] = 0.0;
   out_8671923853756600219[20] = 1.0;
   out_8671923853756600219[21] = 0.0;
   out_8671923853756600219[22] = 0.0;
   out_8671923853756600219[23] = 0.0;
   out_8671923853756600219[24] = 0.0;
   out_8671923853756600219[25] = 0.0;
   out_8671923853756600219[26] = 0.0;
   out_8671923853756600219[27] = 0.0;
   out_8671923853756600219[28] = 0.0;
   out_8671923853756600219[29] = 0.0;
   out_8671923853756600219[30] = 1.0;
   out_8671923853756600219[31] = 0.0;
   out_8671923853756600219[32] = 0.0;
   out_8671923853756600219[33] = 0.0;
   out_8671923853756600219[34] = 0.0;
   out_8671923853756600219[35] = 0.0;
   out_8671923853756600219[36] = 0.0;
   out_8671923853756600219[37] = 0.0;
   out_8671923853756600219[38] = 0.0;
   out_8671923853756600219[39] = 0.0;
   out_8671923853756600219[40] = 1.0;
   out_8671923853756600219[41] = 0.0;
   out_8671923853756600219[42] = 0.0;
   out_8671923853756600219[43] = 0.0;
   out_8671923853756600219[44] = 0.0;
   out_8671923853756600219[45] = 0.0;
   out_8671923853756600219[46] = 0.0;
   out_8671923853756600219[47] = 0.0;
   out_8671923853756600219[48] = 0.0;
   out_8671923853756600219[49] = 0.0;
   out_8671923853756600219[50] = 1.0;
   out_8671923853756600219[51] = 0.0;
   out_8671923853756600219[52] = 0.0;
   out_8671923853756600219[53] = 0.0;
   out_8671923853756600219[54] = 0.0;
   out_8671923853756600219[55] = 0.0;
   out_8671923853756600219[56] = 0.0;
   out_8671923853756600219[57] = 0.0;
   out_8671923853756600219[58] = 0.0;
   out_8671923853756600219[59] = 0.0;
   out_8671923853756600219[60] = 1.0;
   out_8671923853756600219[61] = 0.0;
   out_8671923853756600219[62] = 0.0;
   out_8671923853756600219[63] = 0.0;
   out_8671923853756600219[64] = 0.0;
   out_8671923853756600219[65] = 0.0;
   out_8671923853756600219[66] = 0.0;
   out_8671923853756600219[67] = 0.0;
   out_8671923853756600219[68] = 0.0;
   out_8671923853756600219[69] = 0.0;
   out_8671923853756600219[70] = 1.0;
   out_8671923853756600219[71] = 0.0;
   out_8671923853756600219[72] = 0.0;
   out_8671923853756600219[73] = 0.0;
   out_8671923853756600219[74] = 0.0;
   out_8671923853756600219[75] = 0.0;
   out_8671923853756600219[76] = 0.0;
   out_8671923853756600219[77] = 0.0;
   out_8671923853756600219[78] = 0.0;
   out_8671923853756600219[79] = 0.0;
   out_8671923853756600219[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3762356930851513593) {
   out_3762356930851513593[0] = state[0];
   out_3762356930851513593[1] = state[1];
   out_3762356930851513593[2] = state[2];
   out_3762356930851513593[3] = state[3];
   out_3762356930851513593[4] = state[4];
   out_3762356930851513593[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3762356930851513593[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3762356930851513593[7] = state[7];
   out_3762356930851513593[8] = state[8];
}
void F_fun(double *state, double dt, double *out_110226856445903204) {
   out_110226856445903204[0] = 1;
   out_110226856445903204[1] = 0;
   out_110226856445903204[2] = 0;
   out_110226856445903204[3] = 0;
   out_110226856445903204[4] = 0;
   out_110226856445903204[5] = 0;
   out_110226856445903204[6] = 0;
   out_110226856445903204[7] = 0;
   out_110226856445903204[8] = 0;
   out_110226856445903204[9] = 0;
   out_110226856445903204[10] = 1;
   out_110226856445903204[11] = 0;
   out_110226856445903204[12] = 0;
   out_110226856445903204[13] = 0;
   out_110226856445903204[14] = 0;
   out_110226856445903204[15] = 0;
   out_110226856445903204[16] = 0;
   out_110226856445903204[17] = 0;
   out_110226856445903204[18] = 0;
   out_110226856445903204[19] = 0;
   out_110226856445903204[20] = 1;
   out_110226856445903204[21] = 0;
   out_110226856445903204[22] = 0;
   out_110226856445903204[23] = 0;
   out_110226856445903204[24] = 0;
   out_110226856445903204[25] = 0;
   out_110226856445903204[26] = 0;
   out_110226856445903204[27] = 0;
   out_110226856445903204[28] = 0;
   out_110226856445903204[29] = 0;
   out_110226856445903204[30] = 1;
   out_110226856445903204[31] = 0;
   out_110226856445903204[32] = 0;
   out_110226856445903204[33] = 0;
   out_110226856445903204[34] = 0;
   out_110226856445903204[35] = 0;
   out_110226856445903204[36] = 0;
   out_110226856445903204[37] = 0;
   out_110226856445903204[38] = 0;
   out_110226856445903204[39] = 0;
   out_110226856445903204[40] = 1;
   out_110226856445903204[41] = 0;
   out_110226856445903204[42] = 0;
   out_110226856445903204[43] = 0;
   out_110226856445903204[44] = 0;
   out_110226856445903204[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_110226856445903204[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_110226856445903204[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_110226856445903204[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_110226856445903204[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_110226856445903204[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_110226856445903204[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_110226856445903204[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_110226856445903204[53] = -9.8100000000000005*dt;
   out_110226856445903204[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_110226856445903204[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_110226856445903204[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_110226856445903204[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_110226856445903204[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_110226856445903204[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_110226856445903204[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_110226856445903204[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_110226856445903204[62] = 0;
   out_110226856445903204[63] = 0;
   out_110226856445903204[64] = 0;
   out_110226856445903204[65] = 0;
   out_110226856445903204[66] = 0;
   out_110226856445903204[67] = 0;
   out_110226856445903204[68] = 0;
   out_110226856445903204[69] = 0;
   out_110226856445903204[70] = 1;
   out_110226856445903204[71] = 0;
   out_110226856445903204[72] = 0;
   out_110226856445903204[73] = 0;
   out_110226856445903204[74] = 0;
   out_110226856445903204[75] = 0;
   out_110226856445903204[76] = 0;
   out_110226856445903204[77] = 0;
   out_110226856445903204[78] = 0;
   out_110226856445903204[79] = 0;
   out_110226856445903204[80] = 1;
}
void h_25(double *state, double *unused, double *out_5646094358831955306) {
   out_5646094358831955306[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4871128394768286557) {
   out_4871128394768286557[0] = 0;
   out_4871128394768286557[1] = 0;
   out_4871128394768286557[2] = 0;
   out_4871128394768286557[3] = 0;
   out_4871128394768286557[4] = 0;
   out_4871128394768286557[5] = 0;
   out_4871128394768286557[6] = 1;
   out_4871128394768286557[7] = 0;
   out_4871128394768286557[8] = 0;
}
void h_24(double *state, double *unused, double *out_7079061790558552168) {
   out_7079061790558552168[0] = state[4];
   out_7079061790558552168[1] = state[5];
}
void H_24(double *state, double *unused, double *out_7374582999090103633) {
   out_7374582999090103633[0] = 0;
   out_7374582999090103633[1] = 0;
   out_7374582999090103633[2] = 0;
   out_7374582999090103633[3] = 0;
   out_7374582999090103633[4] = 1;
   out_7374582999090103633[5] = 0;
   out_7374582999090103633[6] = 0;
   out_7374582999090103633[7] = 0;
   out_7374582999090103633[8] = 0;
   out_7374582999090103633[9] = 0;
   out_7374582999090103633[10] = 0;
   out_7374582999090103633[11] = 0;
   out_7374582999090103633[12] = 0;
   out_7374582999090103633[13] = 0;
   out_7374582999090103633[14] = 1;
   out_7374582999090103633[15] = 0;
   out_7374582999090103633[16] = 0;
   out_7374582999090103633[17] = 0;
}
void h_30(double *state, double *unused, double *out_2117170897988717135) {
   out_2117170897988717135[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2352795436261037930) {
   out_2352795436261037930[0] = 0;
   out_2352795436261037930[1] = 0;
   out_2352795436261037930[2] = 0;
   out_2352795436261037930[3] = 0;
   out_2352795436261037930[4] = 1;
   out_2352795436261037930[5] = 0;
   out_2352795436261037930[6] = 0;
   out_2352795436261037930[7] = 0;
   out_2352795436261037930[8] = 0;
}
void h_26(double *state, double *unused, double *out_7183588416707059858) {
   out_7183588416707059858[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8612631713642342781) {
   out_8612631713642342781[0] = 0;
   out_8612631713642342781[1] = 0;
   out_8612631713642342781[2] = 0;
   out_8612631713642342781[3] = 0;
   out_8612631713642342781[4] = 0;
   out_8612631713642342781[5] = 0;
   out_8612631713642342781[6] = 0;
   out_8612631713642342781[7] = 1;
   out_8612631713642342781[8] = 0;
}
void h_27(double *state, double *unused, double *out_3041689038023257655) {
   out_3041689038023257655[0] = state[3];
}
void H_27(double *state, double *unused, double *out_129201365077094713) {
   out_129201365077094713[0] = 0;
   out_129201365077094713[1] = 0;
   out_129201365077094713[2] = 0;
   out_129201365077094713[3] = 1;
   out_129201365077094713[4] = 0;
   out_129201365077094713[5] = 0;
   out_129201365077094713[6] = 0;
   out_129201365077094713[7] = 0;
   out_129201365077094713[8] = 0;
}
void h_29(double *state, double *unused, double *out_2884502369672128510) {
   out_2884502369672128510[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1842564091946645746) {
   out_1842564091946645746[0] = 0;
   out_1842564091946645746[1] = 1;
   out_1842564091946645746[2] = 0;
   out_1842564091946645746[3] = 0;
   out_1842564091946645746[4] = 0;
   out_1842564091946645746[5] = 0;
   out_1842564091946645746[6] = 0;
   out_1842564091946645746[7] = 0;
   out_1842564091946645746[8] = 0;
}
void h_28(double *state, double *unused, double *out_4902986578924970) {
   out_4902986578924970[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6924963109016176320) {
   out_6924963109016176320[0] = 1;
   out_6924963109016176320[1] = 0;
   out_6924963109016176320[2] = 0;
   out_6924963109016176320[3] = 0;
   out_6924963109016176320[4] = 0;
   out_6924963109016176320[5] = 0;
   out_6924963109016176320[6] = 0;
   out_6924963109016176320[7] = 0;
   out_6924963109016176320[8] = 0;
}
void h_31(double *state, double *unused, double *out_8547812156113883153) {
   out_8547812156113883153[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4840482432891326129) {
   out_4840482432891326129[0] = 0;
   out_4840482432891326129[1] = 0;
   out_4840482432891326129[2] = 0;
   out_4840482432891326129[3] = 0;
   out_4840482432891326129[4] = 0;
   out_4840482432891326129[5] = 0;
   out_4840482432891326129[6] = 0;
   out_4840482432891326129[7] = 0;
   out_4840482432891326129[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8308214496735031777) {
  err_fun(nom_x, delta_x, out_8308214496735031777);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8999766425853420329) {
  inv_err_fun(nom_x, true_x, out_8999766425853420329);
}
void car_H_mod_fun(double *state, double *out_8671923853756600219) {
  H_mod_fun(state, out_8671923853756600219);
}
void car_f_fun(double *state, double dt, double *out_3762356930851513593) {
  f_fun(state,  dt, out_3762356930851513593);
}
void car_F_fun(double *state, double dt, double *out_110226856445903204) {
  F_fun(state,  dt, out_110226856445903204);
}
void car_h_25(double *state, double *unused, double *out_5646094358831955306) {
  h_25(state, unused, out_5646094358831955306);
}
void car_H_25(double *state, double *unused, double *out_4871128394768286557) {
  H_25(state, unused, out_4871128394768286557);
}
void car_h_24(double *state, double *unused, double *out_7079061790558552168) {
  h_24(state, unused, out_7079061790558552168);
}
void car_H_24(double *state, double *unused, double *out_7374582999090103633) {
  H_24(state, unused, out_7374582999090103633);
}
void car_h_30(double *state, double *unused, double *out_2117170897988717135) {
  h_30(state, unused, out_2117170897988717135);
}
void car_H_30(double *state, double *unused, double *out_2352795436261037930) {
  H_30(state, unused, out_2352795436261037930);
}
void car_h_26(double *state, double *unused, double *out_7183588416707059858) {
  h_26(state, unused, out_7183588416707059858);
}
void car_H_26(double *state, double *unused, double *out_8612631713642342781) {
  H_26(state, unused, out_8612631713642342781);
}
void car_h_27(double *state, double *unused, double *out_3041689038023257655) {
  h_27(state, unused, out_3041689038023257655);
}
void car_H_27(double *state, double *unused, double *out_129201365077094713) {
  H_27(state, unused, out_129201365077094713);
}
void car_h_29(double *state, double *unused, double *out_2884502369672128510) {
  h_29(state, unused, out_2884502369672128510);
}
void car_H_29(double *state, double *unused, double *out_1842564091946645746) {
  H_29(state, unused, out_1842564091946645746);
}
void car_h_28(double *state, double *unused, double *out_4902986578924970) {
  h_28(state, unused, out_4902986578924970);
}
void car_H_28(double *state, double *unused, double *out_6924963109016176320) {
  H_28(state, unused, out_6924963109016176320);
}
void car_h_31(double *state, double *unused, double *out_8547812156113883153) {
  h_31(state, unused, out_8547812156113883153);
}
void car_H_31(double *state, double *unused, double *out_4840482432891326129) {
  H_31(state, unused, out_4840482432891326129);
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
