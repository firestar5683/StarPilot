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
void err_fun(double *nom_x, double *delta_x, double *out_3018178744748463403) {
   out_3018178744748463403[0] = delta_x[0] + nom_x[0];
   out_3018178744748463403[1] = delta_x[1] + nom_x[1];
   out_3018178744748463403[2] = delta_x[2] + nom_x[2];
   out_3018178744748463403[3] = delta_x[3] + nom_x[3];
   out_3018178744748463403[4] = delta_x[4] + nom_x[4];
   out_3018178744748463403[5] = delta_x[5] + nom_x[5];
   out_3018178744748463403[6] = delta_x[6] + nom_x[6];
   out_3018178744748463403[7] = delta_x[7] + nom_x[7];
   out_3018178744748463403[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6060282748917342967) {
   out_6060282748917342967[0] = -nom_x[0] + true_x[0];
   out_6060282748917342967[1] = -nom_x[1] + true_x[1];
   out_6060282748917342967[2] = -nom_x[2] + true_x[2];
   out_6060282748917342967[3] = -nom_x[3] + true_x[3];
   out_6060282748917342967[4] = -nom_x[4] + true_x[4];
   out_6060282748917342967[5] = -nom_x[5] + true_x[5];
   out_6060282748917342967[6] = -nom_x[6] + true_x[6];
   out_6060282748917342967[7] = -nom_x[7] + true_x[7];
   out_6060282748917342967[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2864403739014660828) {
   out_2864403739014660828[0] = 1.0;
   out_2864403739014660828[1] = 0.0;
   out_2864403739014660828[2] = 0.0;
   out_2864403739014660828[3] = 0.0;
   out_2864403739014660828[4] = 0.0;
   out_2864403739014660828[5] = 0.0;
   out_2864403739014660828[6] = 0.0;
   out_2864403739014660828[7] = 0.0;
   out_2864403739014660828[8] = 0.0;
   out_2864403739014660828[9] = 0.0;
   out_2864403739014660828[10] = 1.0;
   out_2864403739014660828[11] = 0.0;
   out_2864403739014660828[12] = 0.0;
   out_2864403739014660828[13] = 0.0;
   out_2864403739014660828[14] = 0.0;
   out_2864403739014660828[15] = 0.0;
   out_2864403739014660828[16] = 0.0;
   out_2864403739014660828[17] = 0.0;
   out_2864403739014660828[18] = 0.0;
   out_2864403739014660828[19] = 0.0;
   out_2864403739014660828[20] = 1.0;
   out_2864403739014660828[21] = 0.0;
   out_2864403739014660828[22] = 0.0;
   out_2864403739014660828[23] = 0.0;
   out_2864403739014660828[24] = 0.0;
   out_2864403739014660828[25] = 0.0;
   out_2864403739014660828[26] = 0.0;
   out_2864403739014660828[27] = 0.0;
   out_2864403739014660828[28] = 0.0;
   out_2864403739014660828[29] = 0.0;
   out_2864403739014660828[30] = 1.0;
   out_2864403739014660828[31] = 0.0;
   out_2864403739014660828[32] = 0.0;
   out_2864403739014660828[33] = 0.0;
   out_2864403739014660828[34] = 0.0;
   out_2864403739014660828[35] = 0.0;
   out_2864403739014660828[36] = 0.0;
   out_2864403739014660828[37] = 0.0;
   out_2864403739014660828[38] = 0.0;
   out_2864403739014660828[39] = 0.0;
   out_2864403739014660828[40] = 1.0;
   out_2864403739014660828[41] = 0.0;
   out_2864403739014660828[42] = 0.0;
   out_2864403739014660828[43] = 0.0;
   out_2864403739014660828[44] = 0.0;
   out_2864403739014660828[45] = 0.0;
   out_2864403739014660828[46] = 0.0;
   out_2864403739014660828[47] = 0.0;
   out_2864403739014660828[48] = 0.0;
   out_2864403739014660828[49] = 0.0;
   out_2864403739014660828[50] = 1.0;
   out_2864403739014660828[51] = 0.0;
   out_2864403739014660828[52] = 0.0;
   out_2864403739014660828[53] = 0.0;
   out_2864403739014660828[54] = 0.0;
   out_2864403739014660828[55] = 0.0;
   out_2864403739014660828[56] = 0.0;
   out_2864403739014660828[57] = 0.0;
   out_2864403739014660828[58] = 0.0;
   out_2864403739014660828[59] = 0.0;
   out_2864403739014660828[60] = 1.0;
   out_2864403739014660828[61] = 0.0;
   out_2864403739014660828[62] = 0.0;
   out_2864403739014660828[63] = 0.0;
   out_2864403739014660828[64] = 0.0;
   out_2864403739014660828[65] = 0.0;
   out_2864403739014660828[66] = 0.0;
   out_2864403739014660828[67] = 0.0;
   out_2864403739014660828[68] = 0.0;
   out_2864403739014660828[69] = 0.0;
   out_2864403739014660828[70] = 1.0;
   out_2864403739014660828[71] = 0.0;
   out_2864403739014660828[72] = 0.0;
   out_2864403739014660828[73] = 0.0;
   out_2864403739014660828[74] = 0.0;
   out_2864403739014660828[75] = 0.0;
   out_2864403739014660828[76] = 0.0;
   out_2864403739014660828[77] = 0.0;
   out_2864403739014660828[78] = 0.0;
   out_2864403739014660828[79] = 0.0;
   out_2864403739014660828[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_5470700188972722037) {
   out_5470700188972722037[0] = state[0];
   out_5470700188972722037[1] = state[1];
   out_5470700188972722037[2] = state[2];
   out_5470700188972722037[3] = state[3];
   out_5470700188972722037[4] = state[4];
   out_5470700188972722037[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_5470700188972722037[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_5470700188972722037[7] = state[7];
   out_5470700188972722037[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7150823736868333707) {
   out_7150823736868333707[0] = 1;
   out_7150823736868333707[1] = 0;
   out_7150823736868333707[2] = 0;
   out_7150823736868333707[3] = 0;
   out_7150823736868333707[4] = 0;
   out_7150823736868333707[5] = 0;
   out_7150823736868333707[6] = 0;
   out_7150823736868333707[7] = 0;
   out_7150823736868333707[8] = 0;
   out_7150823736868333707[9] = 0;
   out_7150823736868333707[10] = 1;
   out_7150823736868333707[11] = 0;
   out_7150823736868333707[12] = 0;
   out_7150823736868333707[13] = 0;
   out_7150823736868333707[14] = 0;
   out_7150823736868333707[15] = 0;
   out_7150823736868333707[16] = 0;
   out_7150823736868333707[17] = 0;
   out_7150823736868333707[18] = 0;
   out_7150823736868333707[19] = 0;
   out_7150823736868333707[20] = 1;
   out_7150823736868333707[21] = 0;
   out_7150823736868333707[22] = 0;
   out_7150823736868333707[23] = 0;
   out_7150823736868333707[24] = 0;
   out_7150823736868333707[25] = 0;
   out_7150823736868333707[26] = 0;
   out_7150823736868333707[27] = 0;
   out_7150823736868333707[28] = 0;
   out_7150823736868333707[29] = 0;
   out_7150823736868333707[30] = 1;
   out_7150823736868333707[31] = 0;
   out_7150823736868333707[32] = 0;
   out_7150823736868333707[33] = 0;
   out_7150823736868333707[34] = 0;
   out_7150823736868333707[35] = 0;
   out_7150823736868333707[36] = 0;
   out_7150823736868333707[37] = 0;
   out_7150823736868333707[38] = 0;
   out_7150823736868333707[39] = 0;
   out_7150823736868333707[40] = 1;
   out_7150823736868333707[41] = 0;
   out_7150823736868333707[42] = 0;
   out_7150823736868333707[43] = 0;
   out_7150823736868333707[44] = 0;
   out_7150823736868333707[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7150823736868333707[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7150823736868333707[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7150823736868333707[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7150823736868333707[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7150823736868333707[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7150823736868333707[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7150823736868333707[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7150823736868333707[53] = -9.8100000000000005*dt;
   out_7150823736868333707[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7150823736868333707[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7150823736868333707[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7150823736868333707[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7150823736868333707[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7150823736868333707[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7150823736868333707[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7150823736868333707[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7150823736868333707[62] = 0;
   out_7150823736868333707[63] = 0;
   out_7150823736868333707[64] = 0;
   out_7150823736868333707[65] = 0;
   out_7150823736868333707[66] = 0;
   out_7150823736868333707[67] = 0;
   out_7150823736868333707[68] = 0;
   out_7150823736868333707[69] = 0;
   out_7150823736868333707[70] = 1;
   out_7150823736868333707[71] = 0;
   out_7150823736868333707[72] = 0;
   out_7150823736868333707[73] = 0;
   out_7150823736868333707[74] = 0;
   out_7150823736868333707[75] = 0;
   out_7150823736868333707[76] = 0;
   out_7150823736868333707[77] = 0;
   out_7150823736868333707[78] = 0;
   out_7150823736868333707[79] = 0;
   out_7150823736868333707[80] = 1;
}
void h_25(double *state, double *unused, double *out_264395063841365559) {
   out_264395063841365559[0] = state[6];
}
void H_25(double *state, double *unused, double *out_8902644214858585877) {
   out_8902644214858585877[0] = 0;
   out_8902644214858585877[1] = 0;
   out_8902644214858585877[2] = 0;
   out_8902644214858585877[3] = 0;
   out_8902644214858585877[4] = 0;
   out_8902644214858585877[5] = 0;
   out_8902644214858585877[6] = 1;
   out_8902644214858585877[7] = 0;
   out_8902644214858585877[8] = 0;
}
void h_24(double *state, double *unused, double *out_5091830536703747687) {
   out_5091830536703747687[0] = state[4];
   out_5091830536703747687[1] = state[5];
}
void H_24(double *state, double *unused, double *out_517398855874799444) {
   out_517398855874799444[0] = 0;
   out_517398855874799444[1] = 0;
   out_517398855874799444[2] = 0;
   out_517398855874799444[3] = 0;
   out_517398855874799444[4] = 1;
   out_517398855874799444[5] = 0;
   out_517398855874799444[6] = 0;
   out_517398855874799444[7] = 0;
   out_517398855874799444[8] = 0;
   out_517398855874799444[9] = 0;
   out_517398855874799444[10] = 0;
   out_517398855874799444[11] = 0;
   out_517398855874799444[12] = 0;
   out_517398855874799444[13] = 0;
   out_517398855874799444[14] = 1;
   out_517398855874799444[15] = 0;
   out_517398855874799444[16] = 0;
   out_517398855874799444[17] = 0;
}
void h_30(double *state, double *unused, double *out_1715026456470248726) {
   out_1715026456470248726[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1985953873366969122) {
   out_1985953873366969122[0] = 0;
   out_1985953873366969122[1] = 0;
   out_1985953873366969122[2] = 0;
   out_1985953873366969122[3] = 0;
   out_1985953873366969122[4] = 1;
   out_1985953873366969122[5] = 0;
   out_1985953873366969122[6] = 0;
   out_1985953873366969122[7] = 0;
   out_1985953873366969122[8] = 0;
}
void h_26(double *state, double *unused, double *out_2318342341146726243) {
   out_2318342341146726243[0] = state[7];
}
void H_26(double *state, double *unused, double *out_5598118245097785276) {
   out_5598118245097785276[0] = 0;
   out_5598118245097785276[1] = 0;
   out_5598118245097785276[2] = 0;
   out_5598118245097785276[3] = 0;
   out_5598118245097785276[4] = 0;
   out_5598118245097785276[5] = 0;
   out_5598118245097785276[6] = 0;
   out_5598118245097785276[7] = 1;
   out_5598118245097785276[8] = 0;
}
void h_27(double *state, double *unused, double *out_717689029493932553) {
   out_717689029493932553[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4160717185167394033) {
   out_4160717185167394033[0] = 0;
   out_4160717185167394033[1] = 0;
   out_4160717185167394033[2] = 0;
   out_4160717185167394033[3] = 1;
   out_4160717185167394033[4] = 0;
   out_4160717185167394033[5] = 0;
   out_4160717185167394033[6] = 0;
   out_4160717185167394033[7] = 0;
   out_4160717185167394033[8] = 0;
}
void h_29(double *state, double *unused, double *out_992883091778438442) {
   out_992883091778438442[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5874079912036945066) {
   out_5874079912036945066[0] = 0;
   out_5874079912036945066[1] = 1;
   out_5874079912036945066[2] = 0;
   out_5874079912036945066[3] = 0;
   out_5874079912036945066[4] = 0;
   out_5874079912036945066[5] = 0;
   out_5874079912036945066[6] = 0;
   out_5874079912036945066[7] = 0;
   out_5874079912036945066[8] = 0;
}
void h_28(double *state, double *unused, double *out_2197617134068279513) {
   out_2197617134068279513[0] = state[0];
}
void H_28(double *state, double *unused, double *out_7490265144603075976) {
   out_7490265144603075976[0] = 1;
   out_7490265144603075976[1] = 0;
   out_7490265144603075976[2] = 0;
   out_7490265144603075976[3] = 0;
   out_7490265144603075976[4] = 0;
   out_7490265144603075976[5] = 0;
   out_7490265144603075976[6] = 0;
   out_7490265144603075976[7] = 0;
   out_7490265144603075976[8] = 0;
}
void h_31(double *state, double *unused, double *out_8145667714595414744) {
   out_8145667714595414744[0] = state[8];
}
void H_31(double *state, double *unused, double *out_1825968964346768624) {
   out_1825968964346768624[0] = 0;
   out_1825968964346768624[1] = 0;
   out_1825968964346768624[2] = 0;
   out_1825968964346768624[3] = 0;
   out_1825968964346768624[4] = 0;
   out_1825968964346768624[5] = 0;
   out_1825968964346768624[6] = 0;
   out_1825968964346768624[7] = 0;
   out_1825968964346768624[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3018178744748463403) {
  err_fun(nom_x, delta_x, out_3018178744748463403);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6060282748917342967) {
  inv_err_fun(nom_x, true_x, out_6060282748917342967);
}
void car_H_mod_fun(double *state, double *out_2864403739014660828) {
  H_mod_fun(state, out_2864403739014660828);
}
void car_f_fun(double *state, double dt, double *out_5470700188972722037) {
  f_fun(state,  dt, out_5470700188972722037);
}
void car_F_fun(double *state, double dt, double *out_7150823736868333707) {
  F_fun(state,  dt, out_7150823736868333707);
}
void car_h_25(double *state, double *unused, double *out_264395063841365559) {
  h_25(state, unused, out_264395063841365559);
}
void car_H_25(double *state, double *unused, double *out_8902644214858585877) {
  H_25(state, unused, out_8902644214858585877);
}
void car_h_24(double *state, double *unused, double *out_5091830536703747687) {
  h_24(state, unused, out_5091830536703747687);
}
void car_H_24(double *state, double *unused, double *out_517398855874799444) {
  H_24(state, unused, out_517398855874799444);
}
void car_h_30(double *state, double *unused, double *out_1715026456470248726) {
  h_30(state, unused, out_1715026456470248726);
}
void car_H_30(double *state, double *unused, double *out_1985953873366969122) {
  H_30(state, unused, out_1985953873366969122);
}
void car_h_26(double *state, double *unused, double *out_2318342341146726243) {
  h_26(state, unused, out_2318342341146726243);
}
void car_H_26(double *state, double *unused, double *out_5598118245097785276) {
  H_26(state, unused, out_5598118245097785276);
}
void car_h_27(double *state, double *unused, double *out_717689029493932553) {
  h_27(state, unused, out_717689029493932553);
}
void car_H_27(double *state, double *unused, double *out_4160717185167394033) {
  H_27(state, unused, out_4160717185167394033);
}
void car_h_29(double *state, double *unused, double *out_992883091778438442) {
  h_29(state, unused, out_992883091778438442);
}
void car_H_29(double *state, double *unused, double *out_5874079912036945066) {
  H_29(state, unused, out_5874079912036945066);
}
void car_h_28(double *state, double *unused, double *out_2197617134068279513) {
  h_28(state, unused, out_2197617134068279513);
}
void car_H_28(double *state, double *unused, double *out_7490265144603075976) {
  H_28(state, unused, out_7490265144603075976);
}
void car_h_31(double *state, double *unused, double *out_8145667714595414744) {
  h_31(state, unused, out_8145667714595414744);
}
void car_H_31(double *state, double *unused, double *out_1825968964346768624) {
  H_31(state, unused, out_1825968964346768624);
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
