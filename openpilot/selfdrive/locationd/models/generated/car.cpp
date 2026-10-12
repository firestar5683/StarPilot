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
void err_fun(double *nom_x, double *delta_x, double *out_7126582961958922662) {
   out_7126582961958922662[0] = delta_x[0] + nom_x[0];
   out_7126582961958922662[1] = delta_x[1] + nom_x[1];
   out_7126582961958922662[2] = delta_x[2] + nom_x[2];
   out_7126582961958922662[3] = delta_x[3] + nom_x[3];
   out_7126582961958922662[4] = delta_x[4] + nom_x[4];
   out_7126582961958922662[5] = delta_x[5] + nom_x[5];
   out_7126582961958922662[6] = delta_x[6] + nom_x[6];
   out_7126582961958922662[7] = delta_x[7] + nom_x[7];
   out_7126582961958922662[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_945533236592444203) {
   out_945533236592444203[0] = -nom_x[0] + true_x[0];
   out_945533236592444203[1] = -nom_x[1] + true_x[1];
   out_945533236592444203[2] = -nom_x[2] + true_x[2];
   out_945533236592444203[3] = -nom_x[3] + true_x[3];
   out_945533236592444203[4] = -nom_x[4] + true_x[4];
   out_945533236592444203[5] = -nom_x[5] + true_x[5];
   out_945533236592444203[6] = -nom_x[6] + true_x[6];
   out_945533236592444203[7] = -nom_x[7] + true_x[7];
   out_945533236592444203[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2778542718740683729) {
   out_2778542718740683729[0] = 1.0;
   out_2778542718740683729[1] = 0.0;
   out_2778542718740683729[2] = 0.0;
   out_2778542718740683729[3] = 0.0;
   out_2778542718740683729[4] = 0.0;
   out_2778542718740683729[5] = 0.0;
   out_2778542718740683729[6] = 0.0;
   out_2778542718740683729[7] = 0.0;
   out_2778542718740683729[8] = 0.0;
   out_2778542718740683729[9] = 0.0;
   out_2778542718740683729[10] = 1.0;
   out_2778542718740683729[11] = 0.0;
   out_2778542718740683729[12] = 0.0;
   out_2778542718740683729[13] = 0.0;
   out_2778542718740683729[14] = 0.0;
   out_2778542718740683729[15] = 0.0;
   out_2778542718740683729[16] = 0.0;
   out_2778542718740683729[17] = 0.0;
   out_2778542718740683729[18] = 0.0;
   out_2778542718740683729[19] = 0.0;
   out_2778542718740683729[20] = 1.0;
   out_2778542718740683729[21] = 0.0;
   out_2778542718740683729[22] = 0.0;
   out_2778542718740683729[23] = 0.0;
   out_2778542718740683729[24] = 0.0;
   out_2778542718740683729[25] = 0.0;
   out_2778542718740683729[26] = 0.0;
   out_2778542718740683729[27] = 0.0;
   out_2778542718740683729[28] = 0.0;
   out_2778542718740683729[29] = 0.0;
   out_2778542718740683729[30] = 1.0;
   out_2778542718740683729[31] = 0.0;
   out_2778542718740683729[32] = 0.0;
   out_2778542718740683729[33] = 0.0;
   out_2778542718740683729[34] = 0.0;
   out_2778542718740683729[35] = 0.0;
   out_2778542718740683729[36] = 0.0;
   out_2778542718740683729[37] = 0.0;
   out_2778542718740683729[38] = 0.0;
   out_2778542718740683729[39] = 0.0;
   out_2778542718740683729[40] = 1.0;
   out_2778542718740683729[41] = 0.0;
   out_2778542718740683729[42] = 0.0;
   out_2778542718740683729[43] = 0.0;
   out_2778542718740683729[44] = 0.0;
   out_2778542718740683729[45] = 0.0;
   out_2778542718740683729[46] = 0.0;
   out_2778542718740683729[47] = 0.0;
   out_2778542718740683729[48] = 0.0;
   out_2778542718740683729[49] = 0.0;
   out_2778542718740683729[50] = 1.0;
   out_2778542718740683729[51] = 0.0;
   out_2778542718740683729[52] = 0.0;
   out_2778542718740683729[53] = 0.0;
   out_2778542718740683729[54] = 0.0;
   out_2778542718740683729[55] = 0.0;
   out_2778542718740683729[56] = 0.0;
   out_2778542718740683729[57] = 0.0;
   out_2778542718740683729[58] = 0.0;
   out_2778542718740683729[59] = 0.0;
   out_2778542718740683729[60] = 1.0;
   out_2778542718740683729[61] = 0.0;
   out_2778542718740683729[62] = 0.0;
   out_2778542718740683729[63] = 0.0;
   out_2778542718740683729[64] = 0.0;
   out_2778542718740683729[65] = 0.0;
   out_2778542718740683729[66] = 0.0;
   out_2778542718740683729[67] = 0.0;
   out_2778542718740683729[68] = 0.0;
   out_2778542718740683729[69] = 0.0;
   out_2778542718740683729[70] = 1.0;
   out_2778542718740683729[71] = 0.0;
   out_2778542718740683729[72] = 0.0;
   out_2778542718740683729[73] = 0.0;
   out_2778542718740683729[74] = 0.0;
   out_2778542718740683729[75] = 0.0;
   out_2778542718740683729[76] = 0.0;
   out_2778542718740683729[77] = 0.0;
   out_2778542718740683729[78] = 0.0;
   out_2778542718740683729[79] = 0.0;
   out_2778542718740683729[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_3017733201534411708) {
   out_3017733201534411708[0] = state[0];
   out_3017733201534411708[1] = state[1];
   out_3017733201534411708[2] = state[2];
   out_3017733201534411708[3] = state[3];
   out_3017733201534411708[4] = state[4];
   out_3017733201534411708[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_3017733201534411708[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_3017733201534411708[7] = state[7];
   out_3017733201534411708[8] = state[8];
}
void F_fun(double *state, double dt, double *out_9105766054919985506) {
   out_9105766054919985506[0] = 1;
   out_9105766054919985506[1] = 0;
   out_9105766054919985506[2] = 0;
   out_9105766054919985506[3] = 0;
   out_9105766054919985506[4] = 0;
   out_9105766054919985506[5] = 0;
   out_9105766054919985506[6] = 0;
   out_9105766054919985506[7] = 0;
   out_9105766054919985506[8] = 0;
   out_9105766054919985506[9] = 0;
   out_9105766054919985506[10] = 1;
   out_9105766054919985506[11] = 0;
   out_9105766054919985506[12] = 0;
   out_9105766054919985506[13] = 0;
   out_9105766054919985506[14] = 0;
   out_9105766054919985506[15] = 0;
   out_9105766054919985506[16] = 0;
   out_9105766054919985506[17] = 0;
   out_9105766054919985506[18] = 0;
   out_9105766054919985506[19] = 0;
   out_9105766054919985506[20] = 1;
   out_9105766054919985506[21] = 0;
   out_9105766054919985506[22] = 0;
   out_9105766054919985506[23] = 0;
   out_9105766054919985506[24] = 0;
   out_9105766054919985506[25] = 0;
   out_9105766054919985506[26] = 0;
   out_9105766054919985506[27] = 0;
   out_9105766054919985506[28] = 0;
   out_9105766054919985506[29] = 0;
   out_9105766054919985506[30] = 1;
   out_9105766054919985506[31] = 0;
   out_9105766054919985506[32] = 0;
   out_9105766054919985506[33] = 0;
   out_9105766054919985506[34] = 0;
   out_9105766054919985506[35] = 0;
   out_9105766054919985506[36] = 0;
   out_9105766054919985506[37] = 0;
   out_9105766054919985506[38] = 0;
   out_9105766054919985506[39] = 0;
   out_9105766054919985506[40] = 1;
   out_9105766054919985506[41] = 0;
   out_9105766054919985506[42] = 0;
   out_9105766054919985506[43] = 0;
   out_9105766054919985506[44] = 0;
   out_9105766054919985506[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_9105766054919985506[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_9105766054919985506[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9105766054919985506[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_9105766054919985506[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_9105766054919985506[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_9105766054919985506[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_9105766054919985506[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_9105766054919985506[53] = -9.8100000000000005*dt;
   out_9105766054919985506[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_9105766054919985506[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_9105766054919985506[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9105766054919985506[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9105766054919985506[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_9105766054919985506[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_9105766054919985506[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_9105766054919985506[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_9105766054919985506[62] = 0;
   out_9105766054919985506[63] = 0;
   out_9105766054919985506[64] = 0;
   out_9105766054919985506[65] = 0;
   out_9105766054919985506[66] = 0;
   out_9105766054919985506[67] = 0;
   out_9105766054919985506[68] = 0;
   out_9105766054919985506[69] = 0;
   out_9105766054919985506[70] = 1;
   out_9105766054919985506[71] = 0;
   out_9105766054919985506[72] = 0;
   out_9105766054919985506[73] = 0;
   out_9105766054919985506[74] = 0;
   out_9105766054919985506[75] = 0;
   out_9105766054919985506[76] = 0;
   out_9105766054919985506[77] = 0;
   out_9105766054919985506[78] = 0;
   out_9105766054919985506[79] = 0;
   out_9105766054919985506[80] = 1;
}
void h_25(double *state, double *unused, double *out_614805040009735499) {
   out_614805040009735499[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2273208276540387017) {
   out_2273208276540387017[0] = 0;
   out_2273208276540387017[1] = 0;
   out_2273208276540387017[2] = 0;
   out_2273208276540387017[3] = 0;
   out_2273208276540387017[4] = 0;
   out_2273208276540387017[5] = 0;
   out_2273208276540387017[6] = 1;
   out_2273208276540387017[7] = 0;
   out_2273208276540387017[8] = 0;
}
void h_24(double *state, double *unused, double *out_217533166938587881) {
   out_217533166938587881[0] = state[4];
   out_217533166938587881[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1728503802090121616) {
   out_1728503802090121616[0] = 0;
   out_1728503802090121616[1] = 0;
   out_1728503802090121616[2] = 0;
   out_1728503802090121616[3] = 0;
   out_1728503802090121616[4] = 1;
   out_1728503802090121616[5] = 0;
   out_1728503802090121616[6] = 0;
   out_1728503802090121616[7] = 0;
   out_1728503802090121616[8] = 0;
   out_1728503802090121616[9] = 0;
   out_1728503802090121616[10] = 0;
   out_1728503802090121616[11] = 0;
   out_1728503802090121616[12] = 0;
   out_1728503802090121616[13] = 0;
   out_1728503802090121616[14] = 1;
   out_1728503802090121616[15] = 0;
   out_1728503802090121616[16] = 0;
   out_1728503802090121616[17] = 0;
}
void h_30(double *state, double *unused, double *out_13386882396371945) {
   out_13386882396371945[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4643482064951229738) {
   out_4643482064951229738[0] = 0;
   out_4643482064951229738[1] = 0;
   out_4643482064951229738[2] = 0;
   out_4643482064951229738[3] = 0;
   out_4643482064951229738[4] = 1;
   out_4643482064951229738[5] = 0;
   out_4643482064951229738[6] = 0;
   out_4643482064951229738[7] = 0;
   out_4643482064951229738[8] = 0;
}
void h_26(double *state, double *unused, double *out_4988286385264473700) {
   out_4988286385264473700[0] = state[7];
}
void H_26(double *state, double *unused, double *out_6014711595414443241) {
   out_6014711595414443241[0] = 0;
   out_6014711595414443241[1] = 0;
   out_6014711595414443241[2] = 0;
   out_6014711595414443241[3] = 0;
   out_6014711595414443241[4] = 0;
   out_6014711595414443241[5] = 0;
   out_6014711595414443241[6] = 0;
   out_6014711595414443241[7] = 1;
   out_6014711595414443241[8] = 0;
}
void h_27(double *state, double *unused, double *out_5616478307670581144) {
   out_5616478307670581144[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2468718753150804827) {
   out_2468718753150804827[0] = 0;
   out_2468718753150804827[1] = 0;
   out_2468718753150804827[2] = 0;
   out_2468718753150804827[3] = 1;
   out_2468718753150804827[4] = 0;
   out_2468718753150804827[5] = 0;
   out_2468718753150804827[6] = 0;
   out_2468718753150804827[7] = 0;
   out_2468718753150804827[8] = 0;
}
void h_29(double *state, double *unused, double *out_8968582289610468820) {
   out_8968582289610468820[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5153713409265621922) {
   out_5153713409265621922[0] = 0;
   out_5153713409265621922[1] = 1;
   out_5153713409265621922[2] = 0;
   out_5153713409265621922[3] = 0;
   out_5153713409265621922[4] = 0;
   out_5153713409265621922[5] = 0;
   out_5153713409265621922[6] = 0;
   out_5153713409265621922[7] = 0;
   out_5153713409265621922[8] = 0;
}
void h_28(double *state, double *unused, double *out_7604358550203645525) {
   out_7604358550203645525[0] = state[0];
}
void H_28(double *state, double *unused, double *out_71314392196091348) {
   out_71314392196091348[0] = 1;
   out_71314392196091348[1] = 0;
   out_71314392196091348[2] = 0;
   out_71314392196091348[3] = 0;
   out_71314392196091348[4] = 0;
   out_71314392196091348[5] = 0;
   out_71314392196091348[6] = 0;
   out_71314392196091348[7] = 0;
   out_71314392196091348[8] = 0;
}
void h_31(double *state, double *unused, double *out_3022644488244286851) {
   out_3022644488244286851[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2242562314663426589) {
   out_2242562314663426589[0] = 0;
   out_2242562314663426589[1] = 0;
   out_2242562314663426589[2] = 0;
   out_2242562314663426589[3] = 0;
   out_2242562314663426589[4] = 0;
   out_2242562314663426589[5] = 0;
   out_2242562314663426589[6] = 0;
   out_2242562314663426589[7] = 0;
   out_2242562314663426589[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_7126582961958922662) {
  err_fun(nom_x, delta_x, out_7126582961958922662);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_945533236592444203) {
  inv_err_fun(nom_x, true_x, out_945533236592444203);
}
void car_H_mod_fun(double *state, double *out_2778542718740683729) {
  H_mod_fun(state, out_2778542718740683729);
}
void car_f_fun(double *state, double dt, double *out_3017733201534411708) {
  f_fun(state,  dt, out_3017733201534411708);
}
void car_F_fun(double *state, double dt, double *out_9105766054919985506) {
  F_fun(state,  dt, out_9105766054919985506);
}
void car_h_25(double *state, double *unused, double *out_614805040009735499) {
  h_25(state, unused, out_614805040009735499);
}
void car_H_25(double *state, double *unused, double *out_2273208276540387017) {
  H_25(state, unused, out_2273208276540387017);
}
void car_h_24(double *state, double *unused, double *out_217533166938587881) {
  h_24(state, unused, out_217533166938587881);
}
void car_H_24(double *state, double *unused, double *out_1728503802090121616) {
  H_24(state, unused, out_1728503802090121616);
}
void car_h_30(double *state, double *unused, double *out_13386882396371945) {
  h_30(state, unused, out_13386882396371945);
}
void car_H_30(double *state, double *unused, double *out_4643482064951229738) {
  H_30(state, unused, out_4643482064951229738);
}
void car_h_26(double *state, double *unused, double *out_4988286385264473700) {
  h_26(state, unused, out_4988286385264473700);
}
void car_H_26(double *state, double *unused, double *out_6014711595414443241) {
  H_26(state, unused, out_6014711595414443241);
}
void car_h_27(double *state, double *unused, double *out_5616478307670581144) {
  h_27(state, unused, out_5616478307670581144);
}
void car_H_27(double *state, double *unused, double *out_2468718753150804827) {
  H_27(state, unused, out_2468718753150804827);
}
void car_h_29(double *state, double *unused, double *out_8968582289610468820) {
  h_29(state, unused, out_8968582289610468820);
}
void car_H_29(double *state, double *unused, double *out_5153713409265621922) {
  H_29(state, unused, out_5153713409265621922);
}
void car_h_28(double *state, double *unused, double *out_7604358550203645525) {
  h_28(state, unused, out_7604358550203645525);
}
void car_H_28(double *state, double *unused, double *out_71314392196091348) {
  H_28(state, unused, out_71314392196091348);
}
void car_h_31(double *state, double *unused, double *out_3022644488244286851) {
  h_31(state, unused, out_3022644488244286851);
}
void car_H_31(double *state, double *unused, double *out_2242562314663426589) {
  H_31(state, unused, out_2242562314663426589);
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
