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
void err_fun(double *nom_x, double *delta_x, double *out_3215893303801496185) {
   out_3215893303801496185[0] = delta_x[0] + nom_x[0];
   out_3215893303801496185[1] = delta_x[1] + nom_x[1];
   out_3215893303801496185[2] = delta_x[2] + nom_x[2];
   out_3215893303801496185[3] = delta_x[3] + nom_x[3];
   out_3215893303801496185[4] = delta_x[4] + nom_x[4];
   out_3215893303801496185[5] = delta_x[5] + nom_x[5];
   out_3215893303801496185[6] = delta_x[6] + nom_x[6];
   out_3215893303801496185[7] = delta_x[7] + nom_x[7];
   out_3215893303801496185[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_147534577326453371) {
   out_147534577326453371[0] = -nom_x[0] + true_x[0];
   out_147534577326453371[1] = -nom_x[1] + true_x[1];
   out_147534577326453371[2] = -nom_x[2] + true_x[2];
   out_147534577326453371[3] = -nom_x[3] + true_x[3];
   out_147534577326453371[4] = -nom_x[4] + true_x[4];
   out_147534577326453371[5] = -nom_x[5] + true_x[5];
   out_147534577326453371[6] = -nom_x[6] + true_x[6];
   out_147534577326453371[7] = -nom_x[7] + true_x[7];
   out_147534577326453371[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2952331916524662835) {
   out_2952331916524662835[0] = 1.0;
   out_2952331916524662835[1] = 0.0;
   out_2952331916524662835[2] = 0.0;
   out_2952331916524662835[3] = 0.0;
   out_2952331916524662835[4] = 0.0;
   out_2952331916524662835[5] = 0.0;
   out_2952331916524662835[6] = 0.0;
   out_2952331916524662835[7] = 0.0;
   out_2952331916524662835[8] = 0.0;
   out_2952331916524662835[9] = 0.0;
   out_2952331916524662835[10] = 1.0;
   out_2952331916524662835[11] = 0.0;
   out_2952331916524662835[12] = 0.0;
   out_2952331916524662835[13] = 0.0;
   out_2952331916524662835[14] = 0.0;
   out_2952331916524662835[15] = 0.0;
   out_2952331916524662835[16] = 0.0;
   out_2952331916524662835[17] = 0.0;
   out_2952331916524662835[18] = 0.0;
   out_2952331916524662835[19] = 0.0;
   out_2952331916524662835[20] = 1.0;
   out_2952331916524662835[21] = 0.0;
   out_2952331916524662835[22] = 0.0;
   out_2952331916524662835[23] = 0.0;
   out_2952331916524662835[24] = 0.0;
   out_2952331916524662835[25] = 0.0;
   out_2952331916524662835[26] = 0.0;
   out_2952331916524662835[27] = 0.0;
   out_2952331916524662835[28] = 0.0;
   out_2952331916524662835[29] = 0.0;
   out_2952331916524662835[30] = 1.0;
   out_2952331916524662835[31] = 0.0;
   out_2952331916524662835[32] = 0.0;
   out_2952331916524662835[33] = 0.0;
   out_2952331916524662835[34] = 0.0;
   out_2952331916524662835[35] = 0.0;
   out_2952331916524662835[36] = 0.0;
   out_2952331916524662835[37] = 0.0;
   out_2952331916524662835[38] = 0.0;
   out_2952331916524662835[39] = 0.0;
   out_2952331916524662835[40] = 1.0;
   out_2952331916524662835[41] = 0.0;
   out_2952331916524662835[42] = 0.0;
   out_2952331916524662835[43] = 0.0;
   out_2952331916524662835[44] = 0.0;
   out_2952331916524662835[45] = 0.0;
   out_2952331916524662835[46] = 0.0;
   out_2952331916524662835[47] = 0.0;
   out_2952331916524662835[48] = 0.0;
   out_2952331916524662835[49] = 0.0;
   out_2952331916524662835[50] = 1.0;
   out_2952331916524662835[51] = 0.0;
   out_2952331916524662835[52] = 0.0;
   out_2952331916524662835[53] = 0.0;
   out_2952331916524662835[54] = 0.0;
   out_2952331916524662835[55] = 0.0;
   out_2952331916524662835[56] = 0.0;
   out_2952331916524662835[57] = 0.0;
   out_2952331916524662835[58] = 0.0;
   out_2952331916524662835[59] = 0.0;
   out_2952331916524662835[60] = 1.0;
   out_2952331916524662835[61] = 0.0;
   out_2952331916524662835[62] = 0.0;
   out_2952331916524662835[63] = 0.0;
   out_2952331916524662835[64] = 0.0;
   out_2952331916524662835[65] = 0.0;
   out_2952331916524662835[66] = 0.0;
   out_2952331916524662835[67] = 0.0;
   out_2952331916524662835[68] = 0.0;
   out_2952331916524662835[69] = 0.0;
   out_2952331916524662835[70] = 1.0;
   out_2952331916524662835[71] = 0.0;
   out_2952331916524662835[72] = 0.0;
   out_2952331916524662835[73] = 0.0;
   out_2952331916524662835[74] = 0.0;
   out_2952331916524662835[75] = 0.0;
   out_2952331916524662835[76] = 0.0;
   out_2952331916524662835[77] = 0.0;
   out_2952331916524662835[78] = 0.0;
   out_2952331916524662835[79] = 0.0;
   out_2952331916524662835[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_1642637227976725443) {
   out_1642637227976725443[0] = state[0];
   out_1642637227976725443[1] = state[1];
   out_1642637227976725443[2] = state[2];
   out_1642637227976725443[3] = state[3];
   out_1642637227976725443[4] = state[4];
   out_1642637227976725443[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_1642637227976725443[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_1642637227976725443[7] = state[7];
   out_1642637227976725443[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6364337859915327156) {
   out_6364337859915327156[0] = 1;
   out_6364337859915327156[1] = 0;
   out_6364337859915327156[2] = 0;
   out_6364337859915327156[3] = 0;
   out_6364337859915327156[4] = 0;
   out_6364337859915327156[5] = 0;
   out_6364337859915327156[6] = 0;
   out_6364337859915327156[7] = 0;
   out_6364337859915327156[8] = 0;
   out_6364337859915327156[9] = 0;
   out_6364337859915327156[10] = 1;
   out_6364337859915327156[11] = 0;
   out_6364337859915327156[12] = 0;
   out_6364337859915327156[13] = 0;
   out_6364337859915327156[14] = 0;
   out_6364337859915327156[15] = 0;
   out_6364337859915327156[16] = 0;
   out_6364337859915327156[17] = 0;
   out_6364337859915327156[18] = 0;
   out_6364337859915327156[19] = 0;
   out_6364337859915327156[20] = 1;
   out_6364337859915327156[21] = 0;
   out_6364337859915327156[22] = 0;
   out_6364337859915327156[23] = 0;
   out_6364337859915327156[24] = 0;
   out_6364337859915327156[25] = 0;
   out_6364337859915327156[26] = 0;
   out_6364337859915327156[27] = 0;
   out_6364337859915327156[28] = 0;
   out_6364337859915327156[29] = 0;
   out_6364337859915327156[30] = 1;
   out_6364337859915327156[31] = 0;
   out_6364337859915327156[32] = 0;
   out_6364337859915327156[33] = 0;
   out_6364337859915327156[34] = 0;
   out_6364337859915327156[35] = 0;
   out_6364337859915327156[36] = 0;
   out_6364337859915327156[37] = 0;
   out_6364337859915327156[38] = 0;
   out_6364337859915327156[39] = 0;
   out_6364337859915327156[40] = 1;
   out_6364337859915327156[41] = 0;
   out_6364337859915327156[42] = 0;
   out_6364337859915327156[43] = 0;
   out_6364337859915327156[44] = 0;
   out_6364337859915327156[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6364337859915327156[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6364337859915327156[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6364337859915327156[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6364337859915327156[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6364337859915327156[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6364337859915327156[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6364337859915327156[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6364337859915327156[53] = -9.8100000000000005*dt;
   out_6364337859915327156[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6364337859915327156[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6364337859915327156[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6364337859915327156[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6364337859915327156[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6364337859915327156[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6364337859915327156[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6364337859915327156[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6364337859915327156[62] = 0;
   out_6364337859915327156[63] = 0;
   out_6364337859915327156[64] = 0;
   out_6364337859915327156[65] = 0;
   out_6364337859915327156[66] = 0;
   out_6364337859915327156[67] = 0;
   out_6364337859915327156[68] = 0;
   out_6364337859915327156[69] = 0;
   out_6364337859915327156[70] = 1;
   out_6364337859915327156[71] = 0;
   out_6364337859915327156[72] = 0;
   out_6364337859915327156[73] = 0;
   out_6364337859915327156[74] = 0;
   out_6364337859915327156[75] = 0;
   out_6364337859915327156[76] = 0;
   out_6364337859915327156[77] = 0;
   out_6364337859915327156[78] = 0;
   out_6364337859915327156[79] = 0;
   out_6364337859915327156[80] = 1;
}
void h_25(double *state, double *unused, double *out_8813185365055608935) {
   out_8813185365055608935[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6475312566514154512) {
   out_6475312566514154512[0] = 0;
   out_6475312566514154512[1] = 0;
   out_6475312566514154512[2] = 0;
   out_6475312566514154512[3] = 0;
   out_6475312566514154512[4] = 0;
   out_6475312566514154512[5] = 0;
   out_6475312566514154512[6] = 1;
   out_6475312566514154512[7] = 0;
   out_6475312566514154512[8] = 0;
}
void h_24(double *state, double *unused, double *out_3661129537260875279) {
   out_3661129537260875279[0] = state[4];
   out_3661129537260875279[1] = state[5];
}
void H_24(double *state, double *unused, double *out_5317226049087211347) {
   out_5317226049087211347[0] = 0;
   out_5317226049087211347[1] = 0;
   out_5317226049087211347[2] = 0;
   out_5317226049087211347[3] = 0;
   out_5317226049087211347[4] = 1;
   out_5317226049087211347[5] = 0;
   out_5317226049087211347[6] = 0;
   out_5317226049087211347[7] = 0;
   out_5317226049087211347[8] = 0;
   out_5317226049087211347[9] = 0;
   out_5317226049087211347[10] = 0;
   out_5317226049087211347[11] = 0;
   out_5317226049087211347[12] = 0;
   out_5317226049087211347[13] = 0;
   out_5317226049087211347[14] = 1;
   out_5317226049087211347[15] = 0;
   out_5317226049087211347[16] = 0;
   out_5317226049087211347[17] = 0;
}
void h_30(double *state, double *unused, double *out_5175735836801586585) {
   out_5175735836801586585[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1947616236386546314) {
   out_1947616236386546314[0] = 0;
   out_1947616236386546314[1] = 0;
   out_1947616236386546314[2] = 0;
   out_1947616236386546314[3] = 0;
   out_1947616236386546314[4] = 1;
   out_1947616236386546314[5] = 0;
   out_1947616236386546314[6] = 0;
   out_1947616236386546314[7] = 0;
   out_1947616236386546314[8] = 0;
}
void h_26(double *state, double *unused, double *out_2138949785357253900) {
   out_2138949785357253900[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2733809247640098288) {
   out_2733809247640098288[0] = 0;
   out_2733809247640098288[1] = 0;
   out_2733809247640098288[2] = 0;
   out_2733809247640098288[3] = 0;
   out_2733809247640098288[4] = 0;
   out_2733809247640098288[5] = 0;
   out_2733809247640098288[6] = 0;
   out_2733809247640098288[7] = 1;
   out_2733809247640098288[8] = 0;
}
void h_27(double *state, double *unused, double *out_8690048855752280246) {
   out_8690048855752280246[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4171210307570489531) {
   out_4171210307570489531[0] = 0;
   out_4171210307570489531[1] = 0;
   out_4171210307570489531[2] = 0;
   out_4171210307570489531[3] = 1;
   out_4171210307570489531[4] = 0;
   out_4171210307570489531[5] = 0;
   out_4171210307570489531[6] = 0;
   out_4171210307570489531[7] = 0;
   out_4171210307570489531[8] = 0;
}
void h_29(double *state, double *unused, double *out_50171379033738362) {
   out_50171379033738362[0] = state[1];
}
void H_29(double *state, double *unused, double *out_2457847580700938498) {
   out_2457847580700938498[0] = 0;
   out_2457847580700938498[1] = 1;
   out_2457847580700938498[2] = 0;
   out_2457847580700938498[3] = 0;
   out_2457847580700938498[4] = 0;
   out_2457847580700938498[5] = 0;
   out_2457847580700938498[6] = 0;
   out_2457847580700938498[7] = 0;
   out_2457847580700938498[8] = 0;
}
void h_28(double *state, double *unused, double *out_1254905421323579433) {
   out_1254905421323579433[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4421477852266264749) {
   out_4421477852266264749[0] = 1;
   out_4421477852266264749[1] = 0;
   out_4421477852266264749[2] = 0;
   out_4421477852266264749[3] = 0;
   out_4421477852266264749[4] = 0;
   out_4421477852266264749[5] = 0;
   out_4421477852266264749[6] = 0;
   out_4421477852266264749[7] = 0;
   out_4421477852266264749[8] = 0;
}
void h_31(double *state, double *unused, double *out_2666243543972910187) {
   out_2666243543972910187[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6505958528391114940) {
   out_6505958528391114940[0] = 0;
   out_6505958528391114940[1] = 0;
   out_6505958528391114940[2] = 0;
   out_6505958528391114940[3] = 0;
   out_6505958528391114940[4] = 0;
   out_6505958528391114940[5] = 0;
   out_6505958528391114940[6] = 0;
   out_6505958528391114940[7] = 0;
   out_6505958528391114940[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3215893303801496185) {
  err_fun(nom_x, delta_x, out_3215893303801496185);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_147534577326453371) {
  inv_err_fun(nom_x, true_x, out_147534577326453371);
}
void car_H_mod_fun(double *state, double *out_2952331916524662835) {
  H_mod_fun(state, out_2952331916524662835);
}
void car_f_fun(double *state, double dt, double *out_1642637227976725443) {
  f_fun(state,  dt, out_1642637227976725443);
}
void car_F_fun(double *state, double dt, double *out_6364337859915327156) {
  F_fun(state,  dt, out_6364337859915327156);
}
void car_h_25(double *state, double *unused, double *out_8813185365055608935) {
  h_25(state, unused, out_8813185365055608935);
}
void car_H_25(double *state, double *unused, double *out_6475312566514154512) {
  H_25(state, unused, out_6475312566514154512);
}
void car_h_24(double *state, double *unused, double *out_3661129537260875279) {
  h_24(state, unused, out_3661129537260875279);
}
void car_H_24(double *state, double *unused, double *out_5317226049087211347) {
  H_24(state, unused, out_5317226049087211347);
}
void car_h_30(double *state, double *unused, double *out_5175735836801586585) {
  h_30(state, unused, out_5175735836801586585);
}
void car_H_30(double *state, double *unused, double *out_1947616236386546314) {
  H_30(state, unused, out_1947616236386546314);
}
void car_h_26(double *state, double *unused, double *out_2138949785357253900) {
  h_26(state, unused, out_2138949785357253900);
}
void car_H_26(double *state, double *unused, double *out_2733809247640098288) {
  H_26(state, unused, out_2733809247640098288);
}
void car_h_27(double *state, double *unused, double *out_8690048855752280246) {
  h_27(state, unused, out_8690048855752280246);
}
void car_H_27(double *state, double *unused, double *out_4171210307570489531) {
  H_27(state, unused, out_4171210307570489531);
}
void car_h_29(double *state, double *unused, double *out_50171379033738362) {
  h_29(state, unused, out_50171379033738362);
}
void car_H_29(double *state, double *unused, double *out_2457847580700938498) {
  H_29(state, unused, out_2457847580700938498);
}
void car_h_28(double *state, double *unused, double *out_1254905421323579433) {
  h_28(state, unused, out_1254905421323579433);
}
void car_H_28(double *state, double *unused, double *out_4421477852266264749) {
  H_28(state, unused, out_4421477852266264749);
}
void car_h_31(double *state, double *unused, double *out_2666243543972910187) {
  h_31(state, unused, out_2666243543972910187);
}
void car_H_31(double *state, double *unused, double *out_6505958528391114940) {
  H_31(state, unused, out_6505958528391114940);
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
