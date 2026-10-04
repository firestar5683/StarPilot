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
void err_fun(double *nom_x, double *delta_x, double *out_5329235690424269818) {
   out_5329235690424269818[0] = delta_x[0] + nom_x[0];
   out_5329235690424269818[1] = delta_x[1] + nom_x[1];
   out_5329235690424269818[2] = delta_x[2] + nom_x[2];
   out_5329235690424269818[3] = delta_x[3] + nom_x[3];
   out_5329235690424269818[4] = delta_x[4] + nom_x[4];
   out_5329235690424269818[5] = delta_x[5] + nom_x[5];
   out_5329235690424269818[6] = delta_x[6] + nom_x[6];
   out_5329235690424269818[7] = delta_x[7] + nom_x[7];
   out_5329235690424269818[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7042239097531323453) {
   out_7042239097531323453[0] = -nom_x[0] + true_x[0];
   out_7042239097531323453[1] = -nom_x[1] + true_x[1];
   out_7042239097531323453[2] = -nom_x[2] + true_x[2];
   out_7042239097531323453[3] = -nom_x[3] + true_x[3];
   out_7042239097531323453[4] = -nom_x[4] + true_x[4];
   out_7042239097531323453[5] = -nom_x[5] + true_x[5];
   out_7042239097531323453[6] = -nom_x[6] + true_x[6];
   out_7042239097531323453[7] = -nom_x[7] + true_x[7];
   out_7042239097531323453[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2752254269287091020) {
   out_2752254269287091020[0] = 1.0;
   out_2752254269287091020[1] = 0.0;
   out_2752254269287091020[2] = 0.0;
   out_2752254269287091020[3] = 0.0;
   out_2752254269287091020[4] = 0.0;
   out_2752254269287091020[5] = 0.0;
   out_2752254269287091020[6] = 0.0;
   out_2752254269287091020[7] = 0.0;
   out_2752254269287091020[8] = 0.0;
   out_2752254269287091020[9] = 0.0;
   out_2752254269287091020[10] = 1.0;
   out_2752254269287091020[11] = 0.0;
   out_2752254269287091020[12] = 0.0;
   out_2752254269287091020[13] = 0.0;
   out_2752254269287091020[14] = 0.0;
   out_2752254269287091020[15] = 0.0;
   out_2752254269287091020[16] = 0.0;
   out_2752254269287091020[17] = 0.0;
   out_2752254269287091020[18] = 0.0;
   out_2752254269287091020[19] = 0.0;
   out_2752254269287091020[20] = 1.0;
   out_2752254269287091020[21] = 0.0;
   out_2752254269287091020[22] = 0.0;
   out_2752254269287091020[23] = 0.0;
   out_2752254269287091020[24] = 0.0;
   out_2752254269287091020[25] = 0.0;
   out_2752254269287091020[26] = 0.0;
   out_2752254269287091020[27] = 0.0;
   out_2752254269287091020[28] = 0.0;
   out_2752254269287091020[29] = 0.0;
   out_2752254269287091020[30] = 1.0;
   out_2752254269287091020[31] = 0.0;
   out_2752254269287091020[32] = 0.0;
   out_2752254269287091020[33] = 0.0;
   out_2752254269287091020[34] = 0.0;
   out_2752254269287091020[35] = 0.0;
   out_2752254269287091020[36] = 0.0;
   out_2752254269287091020[37] = 0.0;
   out_2752254269287091020[38] = 0.0;
   out_2752254269287091020[39] = 0.0;
   out_2752254269287091020[40] = 1.0;
   out_2752254269287091020[41] = 0.0;
   out_2752254269287091020[42] = 0.0;
   out_2752254269287091020[43] = 0.0;
   out_2752254269287091020[44] = 0.0;
   out_2752254269287091020[45] = 0.0;
   out_2752254269287091020[46] = 0.0;
   out_2752254269287091020[47] = 0.0;
   out_2752254269287091020[48] = 0.0;
   out_2752254269287091020[49] = 0.0;
   out_2752254269287091020[50] = 1.0;
   out_2752254269287091020[51] = 0.0;
   out_2752254269287091020[52] = 0.0;
   out_2752254269287091020[53] = 0.0;
   out_2752254269287091020[54] = 0.0;
   out_2752254269287091020[55] = 0.0;
   out_2752254269287091020[56] = 0.0;
   out_2752254269287091020[57] = 0.0;
   out_2752254269287091020[58] = 0.0;
   out_2752254269287091020[59] = 0.0;
   out_2752254269287091020[60] = 1.0;
   out_2752254269287091020[61] = 0.0;
   out_2752254269287091020[62] = 0.0;
   out_2752254269287091020[63] = 0.0;
   out_2752254269287091020[64] = 0.0;
   out_2752254269287091020[65] = 0.0;
   out_2752254269287091020[66] = 0.0;
   out_2752254269287091020[67] = 0.0;
   out_2752254269287091020[68] = 0.0;
   out_2752254269287091020[69] = 0.0;
   out_2752254269287091020[70] = 1.0;
   out_2752254269287091020[71] = 0.0;
   out_2752254269287091020[72] = 0.0;
   out_2752254269287091020[73] = 0.0;
   out_2752254269287091020[74] = 0.0;
   out_2752254269287091020[75] = 0.0;
   out_2752254269287091020[76] = 0.0;
   out_2752254269287091020[77] = 0.0;
   out_2752254269287091020[78] = 0.0;
   out_2752254269287091020[79] = 0.0;
   out_2752254269287091020[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2793650179421741975) {
   out_2793650179421741975[0] = state[0];
   out_2793650179421741975[1] = state[1];
   out_2793650179421741975[2] = state[2];
   out_2793650179421741975[3] = state[3];
   out_2793650179421741975[4] = state[4];
   out_2793650179421741975[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2793650179421741975[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2793650179421741975[7] = state[7];
   out_2793650179421741975[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6729394396829861715) {
   out_6729394396829861715[0] = 1;
   out_6729394396829861715[1] = 0;
   out_6729394396829861715[2] = 0;
   out_6729394396829861715[3] = 0;
   out_6729394396829861715[4] = 0;
   out_6729394396829861715[5] = 0;
   out_6729394396829861715[6] = 0;
   out_6729394396829861715[7] = 0;
   out_6729394396829861715[8] = 0;
   out_6729394396829861715[9] = 0;
   out_6729394396829861715[10] = 1;
   out_6729394396829861715[11] = 0;
   out_6729394396829861715[12] = 0;
   out_6729394396829861715[13] = 0;
   out_6729394396829861715[14] = 0;
   out_6729394396829861715[15] = 0;
   out_6729394396829861715[16] = 0;
   out_6729394396829861715[17] = 0;
   out_6729394396829861715[18] = 0;
   out_6729394396829861715[19] = 0;
   out_6729394396829861715[20] = 1;
   out_6729394396829861715[21] = 0;
   out_6729394396829861715[22] = 0;
   out_6729394396829861715[23] = 0;
   out_6729394396829861715[24] = 0;
   out_6729394396829861715[25] = 0;
   out_6729394396829861715[26] = 0;
   out_6729394396829861715[27] = 0;
   out_6729394396829861715[28] = 0;
   out_6729394396829861715[29] = 0;
   out_6729394396829861715[30] = 1;
   out_6729394396829861715[31] = 0;
   out_6729394396829861715[32] = 0;
   out_6729394396829861715[33] = 0;
   out_6729394396829861715[34] = 0;
   out_6729394396829861715[35] = 0;
   out_6729394396829861715[36] = 0;
   out_6729394396829861715[37] = 0;
   out_6729394396829861715[38] = 0;
   out_6729394396829861715[39] = 0;
   out_6729394396829861715[40] = 1;
   out_6729394396829861715[41] = 0;
   out_6729394396829861715[42] = 0;
   out_6729394396829861715[43] = 0;
   out_6729394396829861715[44] = 0;
   out_6729394396829861715[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6729394396829861715[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6729394396829861715[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6729394396829861715[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6729394396829861715[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6729394396829861715[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6729394396829861715[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6729394396829861715[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6729394396829861715[53] = -9.8100000000000005*dt;
   out_6729394396829861715[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6729394396829861715[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6729394396829861715[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6729394396829861715[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6729394396829861715[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6729394396829861715[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6729394396829861715[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6729394396829861715[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6729394396829861715[62] = 0;
   out_6729394396829861715[63] = 0;
   out_6729394396829861715[64] = 0;
   out_6729394396829861715[65] = 0;
   out_6729394396829861715[66] = 0;
   out_6729394396829861715[67] = 0;
   out_6729394396829861715[68] = 0;
   out_6729394396829861715[69] = 0;
   out_6729394396829861715[70] = 1;
   out_6729394396829861715[71] = 0;
   out_6729394396829861715[72] = 0;
   out_6729394396829861715[73] = 0;
   out_6729394396829861715[74] = 0;
   out_6729394396829861715[75] = 0;
   out_6729394396829861715[76] = 0;
   out_6729394396829861715[77] = 0;
   out_6729394396829861715[78] = 0;
   out_6729394396829861715[79] = 0;
   out_6729394396829861715[80] = 1;
}
void h_25(double *state, double *unused, double *out_8416223701982646454) {
   out_8416223701982646454[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6275234919276582697) {
   out_6275234919276582697[0] = 0;
   out_6275234919276582697[1] = 0;
   out_6275234919276582697[2] = 0;
   out_6275234919276582697[3] = 0;
   out_6275234919276582697[4] = 0;
   out_6275234919276582697[5] = 0;
   out_6275234919276582697[6] = 1;
   out_6275234919276582697[7] = 0;
   out_6275234919276582697[8] = 0;
}
void h_24(double *state, double *unused, double *out_3705618372733553650) {
   out_3705618372733553650[0] = state[4];
   out_3705618372733553650[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1528725592310073663) {
   out_1528725592310073663[0] = 0;
   out_1528725592310073663[1] = 0;
   out_1528725592310073663[2] = 0;
   out_1528725592310073663[3] = 0;
   out_1528725592310073663[4] = 1;
   out_1528725592310073663[5] = 0;
   out_1528725592310073663[6] = 0;
   out_1528725592310073663[7] = 0;
   out_1528725592310073663[8] = 0;
   out_1528725592310073663[9] = 0;
   out_1528725592310073663[10] = 0;
   out_1528725592310073663[11] = 0;
   out_1528725592310073663[12] = 0;
   out_1528725592310073663[13] = 0;
   out_1528725592310073663[14] = 1;
   out_1528725592310073663[15] = 0;
   out_1528725592310073663[16] = 0;
   out_1528725592310073663[17] = 0;
}
void h_30(double *state, double *unused, double *out_3259685145376554226) {
   out_3259685145376554226[0] = state[4];
}
void H_30(double *state, double *unused, double *out_5254818812941352164) {
   out_5254818812941352164[0] = 0;
   out_5254818812941352164[1] = 0;
   out_5254818812941352164[2] = 0;
   out_5254818812941352164[3] = 0;
   out_5254818812941352164[4] = 1;
   out_5254818812941352164[5] = 0;
   out_5254818812941352164[6] = 0;
   out_5254818812941352164[7] = 0;
   out_5254818812941352164[8] = 0;
}
void h_26(double *state, double *unused, double *out_4427428946452695963) {
   out_4427428946452695963[0] = state[7];
}
void H_26(double *state, double *unused, double *out_6932088983386894601) {
   out_6932088983386894601[0] = 0;
   out_6932088983386894601[1] = 0;
   out_6932088983386894601[2] = 0;
   out_6932088983386894601[3] = 0;
   out_6932088983386894601[4] = 0;
   out_6932088983386894601[5] = 0;
   out_6932088983386894601[6] = 0;
   out_6932088983386894601[7] = 1;
   out_6932088983386894601[8] = 0;
}
void h_27(double *state, double *unused, double *out_3414550434321800809) {
   out_3414550434321800809[0] = state[3];
}
void H_27(double *state, double *unused, double *out_3971132660332917716) {
   out_3971132660332917716[0] = 0;
   out_3971132660332917716[1] = 0;
   out_3971132660332917716[2] = 0;
   out_3971132660332917716[3] = 1;
   out_3971132660332917716[4] = 0;
   out_3971132660332917716[5] = 0;
   out_3971132660332917716[6] = 0;
   out_3971132660332917716[7] = 0;
   out_3971132660332917716[8] = 0;
}
void h_29(double *state, double *unused, double *out_447133042106700843) {
   out_447133042106700843[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6656127316447734811) {
   out_6656127316447734811[0] = 0;
   out_6656127316447734811[1] = 1;
   out_6656127316447734811[2] = 0;
   out_6656127316447734811[3] = 0;
   out_6656127316447734811[4] = 0;
   out_6656127316447734811[5] = 0;
   out_6656127316447734811[6] = 0;
   out_6656127316447734811[7] = 0;
   out_6656127316447734811[8] = 0;
}
void h_28(double *state, double *unused, double *out_1207635595134307505) {
   out_1207635595134307505[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8619757588013061062) {
   out_8619757588013061062[0] = 1;
   out_8619757588013061062[1] = 0;
   out_8619757588013061062[2] = 0;
   out_8619757588013061062[3] = 0;
   out_8619757588013061062[4] = 0;
   out_8619757588013061062[5] = 0;
   out_8619757588013061062[6] = 0;
   out_8619757588013061062[7] = 0;
   out_8619757588013061062[8] = 0;
}
void h_31(double *state, double *unused, double *out_652958445161974013) {
   out_652958445161974013[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6305880881153543125) {
   out_6305880881153543125[0] = 0;
   out_6305880881153543125[1] = 0;
   out_6305880881153543125[2] = 0;
   out_6305880881153543125[3] = 0;
   out_6305880881153543125[4] = 0;
   out_6305880881153543125[5] = 0;
   out_6305880881153543125[6] = 0;
   out_6305880881153543125[7] = 0;
   out_6305880881153543125[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_5329235690424269818) {
  err_fun(nom_x, delta_x, out_5329235690424269818);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7042239097531323453) {
  inv_err_fun(nom_x, true_x, out_7042239097531323453);
}
void car_H_mod_fun(double *state, double *out_2752254269287091020) {
  H_mod_fun(state, out_2752254269287091020);
}
void car_f_fun(double *state, double dt, double *out_2793650179421741975) {
  f_fun(state,  dt, out_2793650179421741975);
}
void car_F_fun(double *state, double dt, double *out_6729394396829861715) {
  F_fun(state,  dt, out_6729394396829861715);
}
void car_h_25(double *state, double *unused, double *out_8416223701982646454) {
  h_25(state, unused, out_8416223701982646454);
}
void car_H_25(double *state, double *unused, double *out_6275234919276582697) {
  H_25(state, unused, out_6275234919276582697);
}
void car_h_24(double *state, double *unused, double *out_3705618372733553650) {
  h_24(state, unused, out_3705618372733553650);
}
void car_H_24(double *state, double *unused, double *out_1528725592310073663) {
  H_24(state, unused, out_1528725592310073663);
}
void car_h_30(double *state, double *unused, double *out_3259685145376554226) {
  h_30(state, unused, out_3259685145376554226);
}
void car_H_30(double *state, double *unused, double *out_5254818812941352164) {
  H_30(state, unused, out_5254818812941352164);
}
void car_h_26(double *state, double *unused, double *out_4427428946452695963) {
  h_26(state, unused, out_4427428946452695963);
}
void car_H_26(double *state, double *unused, double *out_6932088983386894601) {
  H_26(state, unused, out_6932088983386894601);
}
void car_h_27(double *state, double *unused, double *out_3414550434321800809) {
  h_27(state, unused, out_3414550434321800809);
}
void car_H_27(double *state, double *unused, double *out_3971132660332917716) {
  H_27(state, unused, out_3971132660332917716);
}
void car_h_29(double *state, double *unused, double *out_447133042106700843) {
  h_29(state, unused, out_447133042106700843);
}
void car_H_29(double *state, double *unused, double *out_6656127316447734811) {
  H_29(state, unused, out_6656127316447734811);
}
void car_h_28(double *state, double *unused, double *out_1207635595134307505) {
  h_28(state, unused, out_1207635595134307505);
}
void car_H_28(double *state, double *unused, double *out_8619757588013061062) {
  H_28(state, unused, out_8619757588013061062);
}
void car_h_31(double *state, double *unused, double *out_652958445161974013) {
  h_31(state, unused, out_652958445161974013);
}
void car_H_31(double *state, double *unused, double *out_6305880881153543125) {
  H_31(state, unused, out_6305880881153543125);
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
